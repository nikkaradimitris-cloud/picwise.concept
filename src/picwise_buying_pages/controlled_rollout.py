from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class ControlledRolloutDecisionStatus(str, Enum):
    limited_rollout_ready = "limited_rollout_ready"
    keep_in_preview = "keep_in_preview"
    hold_manual_review = "hold_manual_review"
    rollback_required = "rollback_required"
    scale_blocked = "scale_blocked"
    needs_more_observation = "needs_more_observation"


class ControlledRolloutTier(str, Enum):
    none = "none"
    preview_only = "preview_only"
    limited = "limited"
    expanded_candidate = "expanded_candidate"


@dataclass(frozen=True)
class ControlledRolloutPolicy:
    max_limited_rollout_records: int = 25
    allow_sitemap_candidate_flag: bool = True
    allow_expand_beyond_limited: bool = False
    rollout_reversible_required: bool = True
    rollback_reason_tokens: tuple[str, ...] = (
        "rollback",
        "provider_contract_regression",
        "runtime_regression",
        "critical",
    )
    blocker_reason_tokens: tuple[str, ...] = (
        "blocked",
        "reject",
        "quality_gate",
        "index_gate",
        "provider_contract",
    )


@dataclass(frozen=True)
class ControlledRolloutDecision:
    candidate_page_id: str
    slug: str
    source_promotion_status: str
    rollout_status: ControlledRolloutDecisionStatus
    rollout_tier: ControlledRolloutTier
    can_enter_limited_rollout: bool
    can_expand_beyond_limited: bool
    can_be_considered_for_sitemap_later: bool
    requires_manual_review: bool
    requires_rollback: bool
    reasons: tuple[str, ...]
    blocker_reasons: tuple[str, ...]
    review_reasons: tuple[str, ...]
    rollback_reasons: tuple[str, ...]
    evidence_summary: Mapping[str, Any]
    is_public: bool = False
    is_live_sitemap_included: bool = False
    is_mass_publish: bool = False


@dataclass(frozen=True)
class ControlledRolloutBatchResult:
    total_records: int
    limited_rollout_ready_count: int
    keep_in_preview_count: int
    hold_manual_review_count: int
    rollback_required_count: int
    scale_blocked_count: int
    needs_more_observation_count: int
    status_counts: dict[str, int]
    blocker_counts: dict[str, int]
    review_counts: dict[str, int]
    rollback_counts: dict[str, int]
    rollout_tier_counts: dict[str, int]
    can_close_roadmap: bool
    decisions: tuple[ControlledRolloutDecision, ...]


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


def _policy_from_input(policy: ControlledRolloutPolicy | None) -> ControlledRolloutPolicy:
    return policy if policy is not None else ControlledRolloutPolicy()


def _decision_to_payload(decision: ControlledRolloutDecision) -> dict[str, Any]:
    payload = asdict(decision)
    payload["rollout_status"] = decision.rollout_status.value
    payload["rollout_tier"] = decision.rollout_tier.value
    return payload


def _contains_token(texts: Iterable[str], tokens: Iterable[str]) -> bool:
    lowered = [text.lower() for text in texts]
    for token in tokens:
        token_norm = _norm_text(token).lower()
        if token_norm and any(token_norm in text for text in lowered):
            return True
    return False


def _count_by_status(decisions: Iterable[ControlledRolloutDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = decision.rollout_status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_reasons(decisions: Iterable[ControlledRolloutDecision], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        for reason in getattr(decision, attr):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _count_tiers(decisions: Iterable[ControlledRolloutDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = decision.rollout_tier.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def evaluate_controlled_rollout_decision(
    promotion_decision: Mapping[str, Any],
    policy: ControlledRolloutPolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    source = dict(promotion_decision or {})

    candidate_page_id = _norm_text(source.get("candidate_page_id") or "candidate-page-unknown")
    slug = _norm_text(source.get("slug"))
    source_promotion_status = _norm_text(source.get("decision_status"))
    reasons = list(_to_reason_tuple(source.get("reasons")))
    blocker_reasons = list(_to_reason_tuple(source.get("blocker_reasons")))
    review_reasons = list(_to_reason_tuple(source.get("review_reasons")))
    rollback_reasons = list(_to_reason_tuple(source.get("rollback_reasons")))
    source_requires_manual_review = _as_bool(source.get("requires_manual_review"))
    source_requires_rollback = _as_bool(source.get("requires_rollback"))
    source_sitemap_flag = _as_bool(source.get("can_expand_sitemap_candidate"))

    evidence_summary = dict(source.get("evidence_summary") or {})
    evidence_summary.update(
        {
            "source_decision_status": source_promotion_status,
            "source_requires_manual_review": source_requires_manual_review,
            "source_requires_rollback": source_requires_rollback,
            "rollout_reversible_required": resolved_policy.rollout_reversible_required,
        }
    )

    has_rollback_signal = bool(source_requires_rollback or rollback_reasons) or _contains_token(
        [*reasons, *blocker_reasons, *review_reasons, *rollback_reasons],
        resolved_policy.rollback_reason_tokens,
    )
    has_blocker_signal = bool(blocker_reasons) or _contains_token(
        [*reasons, *review_reasons],
        resolved_policy.blocker_reason_tokens,
    )

    rollout_status = ControlledRolloutDecisionStatus.keep_in_preview
    rollout_tier = ControlledRolloutTier.preview_only

    if has_rollback_signal or source_promotion_status == "rollback_required":
        rollout_status = ControlledRolloutDecisionStatus.rollback_required
        rollout_tier = ControlledRolloutTier.none
        if "rollback_signal_detected" not in rollback_reasons:
            rollback_reasons.append("rollback_signal_detected")
        reasons.append("rollback_forces_controlled_rollback")
    elif source_promotion_status == "needs_more_observation":
        rollout_status = ControlledRolloutDecisionStatus.needs_more_observation
        rollout_tier = ControlledRolloutTier.preview_only
        reasons.append("requires_more_observation_before_rollout")
    elif source_promotion_status == "hold_manual_review" or source_requires_manual_review:
        rollout_status = ControlledRolloutDecisionStatus.hold_manual_review
        rollout_tier = ControlledRolloutTier.preview_only
        review_reasons.append("promotion_policy_requires_manual_review")
        reasons.append("manual_review_blocking_limited_rollout")
    elif source_promotion_status == "reject_from_promotion":
        rollout_status = ControlledRolloutDecisionStatus.scale_blocked
        rollout_tier = ControlledRolloutTier.none
        blocker_reasons.append("promotion_rejected_from_scale")
        reasons.append("promotion_reject_blocks_scale")
    elif source_promotion_status == "keep_controlled":
        rollout_status = ControlledRolloutDecisionStatus.keep_in_preview
        rollout_tier = ControlledRolloutTier.preview_only
        reasons.append("promotion_kept_controlled_preview_only")
    elif source_promotion_status == "promoted_to_limited_exposure":
        rollout_status = ControlledRolloutDecisionStatus.limited_rollout_ready
        rollout_tier = ControlledRolloutTier.limited
        reasons.append("promotion_ready_for_controlled_limited_rollout")
    else:
        rollout_status = ControlledRolloutDecisionStatus.scale_blocked
        rollout_tier = ControlledRolloutTier.none
        blocker_reasons.append("unknown_source_promotion_status")
        reasons.append("unknown_promotion_status_blocks_scale")

    if has_blocker_signal and rollout_status == ControlledRolloutDecisionStatus.limited_rollout_ready:
        rollout_status = ControlledRolloutDecisionStatus.scale_blocked
        rollout_tier = ControlledRolloutTier.none
        blocker_reasons.append("blocker_signal_blocks_scale")
        reasons.append("blocker_signal_forces_scale_blocked")
    elif has_blocker_signal and rollout_status == ControlledRolloutDecisionStatus.keep_in_preview:
        rollout_status = ControlledRolloutDecisionStatus.hold_manual_review
        rollout_tier = ControlledRolloutTier.preview_only
        review_reasons.append("blocker_signal_requires_manual_review")
        reasons.append("blocker_signal_forces_manual_review")

    requires_rollback = rollout_status == ControlledRolloutDecisionStatus.rollback_required
    requires_manual_review = rollout_status == ControlledRolloutDecisionStatus.hold_manual_review
    can_enter_limited_rollout = rollout_status == ControlledRolloutDecisionStatus.limited_rollout_ready
    can_expand_beyond_limited = bool(
        can_enter_limited_rollout and resolved_policy.allow_expand_beyond_limited
    )
    can_be_considered_for_sitemap_later = bool(
        can_enter_limited_rollout and resolved_policy.allow_sitemap_candidate_flag and source_sitemap_flag
    )

    if can_expand_beyond_limited:
        rollout_tier = ControlledRolloutTier.expanded_candidate

    decision = ControlledRolloutDecision(
        candidate_page_id=candidate_page_id,
        slug=slug,
        source_promotion_status=source_promotion_status,
        rollout_status=rollout_status,
        rollout_tier=rollout_tier,
        can_enter_limited_rollout=can_enter_limited_rollout,
        can_expand_beyond_limited=can_expand_beyond_limited,
        can_be_considered_for_sitemap_later=can_be_considered_for_sitemap_later,
        requires_manual_review=requires_manual_review,
        requires_rollback=requires_rollback,
        reasons=tuple(dict.fromkeys(_to_reason_tuple(reasons))),
        blocker_reasons=tuple(dict.fromkeys(_to_reason_tuple(blocker_reasons))),
        review_reasons=tuple(dict.fromkeys(_to_reason_tuple(review_reasons))),
        rollback_reasons=tuple(dict.fromkeys(_to_reason_tuple(rollback_reasons))),
        evidence_summary=evidence_summary,
        is_public=False,
        is_live_sitemap_included=False,
        is_mass_publish=False,
    )
    return _decision_to_payload(decision)


def evaluate_controlled_rollout_batch(
    promotion_decisions: Iterable[Mapping[str, Any]],
    policy: ControlledRolloutPolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    normalized = [dict(item) for item in promotion_decisions]
    ordered = list(normalized)

    limited_cap = max(0, _as_int(resolved_policy.max_limited_rollout_records))
    limited_used = 0
    decisions: list[ControlledRolloutDecision] = []

    for source in ordered:
        payload = evaluate_controlled_rollout_decision(source, policy=resolved_policy)
        rollout_status = ControlledRolloutDecisionStatus(payload["rollout_status"])
        rollout_tier = ControlledRolloutTier(payload["rollout_tier"])
        reasons = list(payload["reasons"])
        review_reasons = list(payload["review_reasons"])
        evidence_summary = dict(payload["evidence_summary"])

        if rollout_status == ControlledRolloutDecisionStatus.limited_rollout_ready:
            if limited_used >= limited_cap:
                rollout_status = ControlledRolloutDecisionStatus.keep_in_preview
                rollout_tier = ControlledRolloutTier.preview_only
                payload["can_enter_limited_rollout"] = False
                payload["can_expand_beyond_limited"] = False
                payload["can_be_considered_for_sitemap_later"] = False
                review_reasons.append("outside_max_limited_rollout_records_cap")
                reasons.append("rollout_cap_enforced_keep_in_preview")
            else:
                limited_used += 1

        evidence_summary["max_limited_rollout_records"] = limited_cap
        evidence_summary["limited_rollout_slot_reserved"] = rollout_status == ControlledRolloutDecisionStatus.limited_rollout_ready

        decisions.append(
            ControlledRolloutDecision(
                candidate_page_id=payload["candidate_page_id"],
                slug=payload["slug"],
                source_promotion_status=payload["source_promotion_status"],
                rollout_status=rollout_status,
                rollout_tier=rollout_tier,
                can_enter_limited_rollout=bool(payload["can_enter_limited_rollout"]),
                can_expand_beyond_limited=bool(payload["can_expand_beyond_limited"]),
                can_be_considered_for_sitemap_later=bool(payload["can_be_considered_for_sitemap_later"]),
                requires_manual_review=bool(payload["requires_manual_review"]) or rollout_status == ControlledRolloutDecisionStatus.hold_manual_review,
                requires_rollback=bool(payload["requires_rollback"]) or rollout_status == ControlledRolloutDecisionStatus.rollback_required,
                reasons=tuple(dict.fromkeys(_to_reason_tuple(reasons))),
                blocker_reasons=tuple(payload["blocker_reasons"]),
                review_reasons=tuple(dict.fromkeys(_to_reason_tuple(review_reasons))),
                rollback_reasons=tuple(payload["rollback_reasons"]),
                evidence_summary=evidence_summary,
                is_public=False,
                is_live_sitemap_included=False,
                is_mass_publish=False,
            )
        )

    status_counts = _count_by_status(decisions)
    blocker_counts = _count_reasons(decisions, "blocker_reasons")
    review_counts = _count_reasons(decisions, "review_reasons")
    rollback_counts = _count_reasons(decisions, "rollback_reasons")
    rollout_tier_counts = _count_tiers(decisions)

    limited_ready_count = status_counts.get(ControlledRolloutDecisionStatus.limited_rollout_ready.value, 0)
    keep_count = status_counts.get(ControlledRolloutDecisionStatus.keep_in_preview.value, 0)
    hold_count = status_counts.get(ControlledRolloutDecisionStatus.hold_manual_review.value, 0)
    rollback_count = status_counts.get(ControlledRolloutDecisionStatus.rollback_required.value, 0)
    blocked_count = status_counts.get(ControlledRolloutDecisionStatus.scale_blocked.value, 0)
    needs_more_count = status_counts.get(ControlledRolloutDecisionStatus.needs_more_observation.value, 0)
    total_records = len(decisions)

    can_close_roadmap = bool(
        total_records > 0
        and limited_ready_count == total_records
        and keep_count == 0
        and hold_count == 0
        and rollback_count == 0
        and blocked_count == 0
        and needs_more_count == 0
        and all(not item.is_public for item in decisions)
        and all(not item.is_live_sitemap_included for item in decisions)
        and all(not item.is_mass_publish for item in decisions)
    )

    batch = ControlledRolloutBatchResult(
        total_records=total_records,
        limited_rollout_ready_count=limited_ready_count,
        keep_in_preview_count=keep_count,
        hold_manual_review_count=hold_count,
        rollback_required_count=rollback_count,
        scale_blocked_count=blocked_count,
        needs_more_observation_count=needs_more_count,
        status_counts=status_counts,
        blocker_counts=blocker_counts,
        review_counts=review_counts,
        rollback_counts=rollback_counts,
        rollout_tier_counts=rollout_tier_counts,
        can_close_roadmap=can_close_roadmap,
        decisions=tuple(decisions),
    )

    payload = asdict(batch)
    payload["decisions"] = [_decision_to_payload(item) for item in batch.decisions]
    return payload
