from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class GovernanceDecisionStatus(str, Enum):
    approval_ready = "approval_ready"
    approval_required = "approval_required"
    blocked = "blocked"
    rollback_required = "rollback_required"
    rejected = "rejected"


class ReleaseApprovalStatus(str, Enum):
    not_requested = "not_requested"
    pending_human_approval = "pending_human_approval"
    approved = "approved"
    rejected = "rejected"
    rollback_approved = "rollback_approved"


@dataclass(frozen=True)
class ReleaseGovernancePolicy:
    allowed_source_rollout_statuses: tuple[str, ...] = ("limited_rollout_ready",)
    blocked_source_rollout_statuses: tuple[str, ...] = ("scale_blocked",)
    approval_required_source_rollout_statuses: tuple[str, ...] = (
        "keep_in_preview",
        "hold_manual_review",
        "needs_more_observation",
    )
    rollback_source_rollout_statuses: tuple[str, ...] = ("rollback_required",)
    blocker_reason_tokens: tuple[str, ...] = (
        "blocked",
        "reject",
        "quality_gate",
        "index_gate",
        "provider_contract",
    )
    rollback_reason_tokens: tuple[str, ...] = (
        "rollback",
        "provider_contract_regression",
        "runtime_regression",
        "critical",
    )
    public_publish_allowed: bool = False
    live_sitemap_expansion_allowed: bool = False
    mass_publish_allowed: bool = False
    require_explicit_human_approval: bool = True
    require_no_credentials_or_live_provider_connections: bool = True


@dataclass(frozen=True)
class ReleaseGovernanceDecision:
    candidate_page_id: str
    slug: str
    source_rollout_status: str
    governance_status: GovernanceDecisionStatus
    approval_status: ReleaseApprovalStatus
    requires_human_approval: bool
    can_request_limited_activation: bool
    can_publish_publicly: bool
    can_expand_live_sitemap: bool
    requires_rollback: bool
    blocker_reasons: tuple[str, ...]
    approval_requirements: tuple[str, ...]
    rollback_reasons: tuple[str, ...]
    evidence_summary: Mapping[str, Any]
    audit_events: tuple[str, ...]
    is_public: bool
    is_live_sitemap_included: bool
    is_mass_publish: bool


@dataclass(frozen=True)
class ReleaseAuditRecord:
    audit_id: str
    candidate_page_id: str
    slug: str
    actor: str
    action: str
    governance_status: str
    approval_status: str
    requires_human_approval: bool
    requires_rollback: bool
    notes: str | None
    event_signature: str


@dataclass(frozen=True)
class ReleaseGovernanceBatchResult:
    total_records: int
    approval_ready_count: int
    approval_required_count: int
    blocked_count: int
    rollback_required_count: int
    rejected_count: int
    pending_human_approval_count: int
    approved_count: int
    status_counts: dict[str, int]
    approval_status_counts: dict[str, int]
    blocker_counts: dict[str, int]
    rollback_counts: dict[str, int]
    can_move_to_real_provider_activation_review: bool
    decisions: tuple[ReleaseGovernanceDecision, ...]
    audit_records: tuple[ReleaseAuditRecord, ...]


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


def _to_reason_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        cleaned = [_norm_text(item) for item in value if _norm_text(item)]
        return tuple(dict.fromkeys(cleaned))
    single = _norm_text(value)
    return (single,) if single else tuple()


def _contains_token(texts: Iterable[str], tokens: Iterable[str]) -> bool:
    lowered = [text.lower() for text in texts]
    for token in tokens:
        token_norm = _norm_text(token).lower()
        if token_norm and any(token_norm in text for text in lowered):
            return True
    return False


def _policy_from_input(policy: ReleaseGovernancePolicy | None) -> ReleaseGovernancePolicy:
    return policy if policy is not None else ReleaseGovernancePolicy()


def _approval_status_from_input(approval_status: ReleaseApprovalStatus | str | None) -> ReleaseApprovalStatus:
    if isinstance(approval_status, ReleaseApprovalStatus):
        return approval_status
    normalized = _norm_text(approval_status)
    if not normalized:
        return ReleaseApprovalStatus.not_requested
    try:
        return ReleaseApprovalStatus(normalized)
    except ValueError:
        return ReleaseApprovalStatus.not_requested


def _decision_to_payload(decision: ReleaseGovernanceDecision) -> dict[str, Any]:
    payload = asdict(decision)
    payload["governance_status"] = decision.governance_status.value
    payload["approval_status"] = decision.approval_status.value
    return payload


def _audit_to_payload(record: ReleaseAuditRecord) -> dict[str, Any]:
    return asdict(record)


def _count_by_status(decisions: Iterable[ReleaseGovernanceDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = decision.governance_status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_by_approval_status(decisions: Iterable[ReleaseGovernanceDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = decision.approval_status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_reasons(decisions: Iterable[ReleaseGovernanceDecision], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        reasons = getattr(decision, attr)
        for reason in reasons:
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def evaluate_release_governance_decision(
    rollout_decision: Mapping[str, Any],
    approval_status: ReleaseApprovalStatus | str | None = None,
    policy: ReleaseGovernancePolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    source = dict(rollout_decision or {})

    candidate_page_id = _norm_text(source.get("candidate_page_id") or "candidate-page-unknown")
    slug = _norm_text(source.get("slug"))
    source_rollout_status = _norm_text(source.get("rollout_status"))
    resolved_approval_status = _approval_status_from_input(
        approval_status if approval_status is not None else source.get("approval_status")
    )

    reasons = list(_to_reason_tuple(source.get("reasons")))
    blocker_reasons = list(_to_reason_tuple(source.get("blocker_reasons")))
    review_reasons = list(_to_reason_tuple(source.get("review_reasons")))
    rollback_reasons = list(_to_reason_tuple(source.get("rollback_reasons")))

    source_requires_rollback = _as_bool(source.get("requires_rollback"), default=False)
    source_is_public = _as_bool(source.get("is_public"), default=False)
    source_live_sitemap_included = _as_bool(source.get("is_live_sitemap_included"), default=False)
    source_mass_publish = _as_bool(source.get("is_mass_publish"), default=False)
    source_live_provider_connection = _as_bool(source.get("has_live_provider_connection"), default=False)
    source_credentials_added = _as_bool(source.get("has_credentials"), default=False)

    has_rollout_blocker_signal = source_rollout_status in resolved_policy.blocked_source_rollout_statuses
    has_rollout_rollback_signal = source_rollout_status in resolved_policy.rollback_source_rollout_statuses
    has_rollout_approval_required_signal = (
        source_rollout_status in resolved_policy.approval_required_source_rollout_statuses
    )
    has_blocker_reason_signal = bool(blocker_reasons) or _contains_token(
        [*reasons, *review_reasons],
        resolved_policy.blocker_reason_tokens,
    )
    has_rollback_reason_signal = bool(rollback_reasons) or _contains_token(
        [*reasons, *blocker_reasons, *review_reasons],
        resolved_policy.rollback_reason_tokens,
    )

    if source_is_public and "public_state_detected_in_source" not in blocker_reasons:
        blocker_reasons.append("public_state_detected_in_source")
    if source_live_sitemap_included and "live_sitemap_state_detected_in_source" not in blocker_reasons:
        blocker_reasons.append("live_sitemap_state_detected_in_source")
    if source_mass_publish and "mass_publish_state_detected_in_source" not in blocker_reasons:
        blocker_reasons.append("mass_publish_state_detected_in_source")
    if resolved_policy.require_no_credentials_or_live_provider_connections and source_live_provider_connection:
        blocker_reasons.append("live_provider_connection_not_allowed_in_step11")
    if resolved_policy.require_no_credentials_or_live_provider_connections and source_credentials_added:
        blocker_reasons.append("credentials_not_allowed_in_step11")

    has_runtime_safety_blockers = bool(
        source_is_public
        or source_live_sitemap_included
        or source_mass_publish
        or source_live_provider_connection
        or source_credentials_added
    )

    governance_status = GovernanceDecisionStatus.approval_required
    approval_requirements = [
        "human_approval_must_be_explicit",
        "approval_status_never_assumed",
        "no_public_publish_allowed_in_step11",
        "no_live_sitemap_expansion_allowed_in_step11",
        "no_mass_publish_allowed_in_step11",
        "no_credentials_or_live_provider_connections_in_step11",
    ]

    if source_rollout_status not in resolved_policy.allowed_source_rollout_statuses:
        approval_requirements.append("source_rollout_status_must_be_limited_rollout_ready")

    if resolved_approval_status == ReleaseApprovalStatus.pending_human_approval:
        approval_requirements.append("approval_currently_pending_human_decision")
    elif resolved_approval_status == ReleaseApprovalStatus.not_requested:
        approval_requirements.append("human_approval_not_requested_yet")
    elif resolved_approval_status == ReleaseApprovalStatus.rejected:
        approval_requirements.append("human_approval_rejected_requires_remediation")
    elif resolved_approval_status == ReleaseApprovalStatus.rollback_approved:
        approval_requirements.append("rollback_approved_requires_rollback_execution")

    if (
        has_rollout_rollback_signal
        or has_rollback_reason_signal
        or source_requires_rollback
        or resolved_approval_status == ReleaseApprovalStatus.rollback_approved
    ):
        governance_status = GovernanceDecisionStatus.rollback_required
        rollback_reasons.append("rollback_signal_forces_governance_rollback_required")
    elif has_rollout_blocker_signal or has_runtime_safety_blockers or has_blocker_reason_signal:
        governance_status = GovernanceDecisionStatus.blocked
    elif resolved_approval_status == ReleaseApprovalStatus.rejected:
        governance_status = GovernanceDecisionStatus.rejected
    elif source_rollout_status in resolved_policy.allowed_source_rollout_statuses:
        if resolved_approval_status == ReleaseApprovalStatus.approved:
            governance_status = GovernanceDecisionStatus.approval_ready
        else:
            governance_status = GovernanceDecisionStatus.approval_required
    elif has_rollout_approval_required_signal:
        governance_status = GovernanceDecisionStatus.approval_required
    else:
        governance_status = GovernanceDecisionStatus.blocked
        blocker_reasons.append("unsupported_rollout_status_for_governance")

    requires_human_approval = bool(
        resolved_policy.require_explicit_human_approval
        and source_rollout_status in resolved_policy.allowed_source_rollout_statuses
        and governance_status
        not in {
            GovernanceDecisionStatus.blocked,
            GovernanceDecisionStatus.rollback_required,
            GovernanceDecisionStatus.rejected,
        }
    )
    requires_rollback = governance_status == GovernanceDecisionStatus.rollback_required
    can_request_limited_activation = bool(
        governance_status == GovernanceDecisionStatus.approval_ready
        and resolved_approval_status == ReleaseApprovalStatus.approved
        and not requires_rollback
    )

    can_publish_publicly = False if not resolved_policy.public_publish_allowed else False
    can_expand_live_sitemap = False if not resolved_policy.live_sitemap_expansion_allowed else False
    is_public = False
    is_live_sitemap_included = False
    is_mass_publish = False

    audit_events: list[str] = [
        "step11_release_governance_evaluated",
        f"source_rollout_status:{source_rollout_status or 'unknown'}",
        f"governance_status:{governance_status.value}",
        f"approval_status:{resolved_approval_status.value}",
    ]
    if requires_human_approval:
        audit_events.append("human_approval_required")
    if can_request_limited_activation:
        audit_events.append("limited_activation_review_request_allowed")
    if governance_status == GovernanceDecisionStatus.approval_required:
        audit_events.append("waiting_for_explicit_human_approval")
    if governance_status == GovernanceDecisionStatus.blocked:
        audit_events.append("blocked_by_governance_signals")
    if governance_status == GovernanceDecisionStatus.rejected:
        audit_events.append("human_approval_rejected")
    if requires_rollback:
        audit_events.append("rollback_required_before_any_activation")

    evidence_summary = {
        "source_rollout_status": source_rollout_status,
        "source_requires_rollback": source_requires_rollback,
        "source_is_public": source_is_public,
        "source_live_sitemap_included": source_live_sitemap_included,
        "source_is_mass_publish": source_mass_publish,
        "source_has_live_provider_connection": source_live_provider_connection,
        "source_has_credentials": source_credentials_added,
        "has_blocker_signal": bool(has_rollout_blocker_signal or has_blocker_reason_signal or has_runtime_safety_blockers),
        "has_rollback_signal": bool(has_rollout_rollback_signal or has_rollback_reason_signal or source_requires_rollback),
        "requires_explicit_human_approval": resolved_policy.require_explicit_human_approval,
        "public_publish_allowed_in_step11": False,
        "live_sitemap_expansion_allowed_in_step11": False,
        "mass_publish_allowed_in_step11": False,
        "credentials_or_live_provider_connection_allowed_in_step11": False,
        "approval_status_provided_explicitly": approval_status is not None or "approval_status" in source,
    }

    decision = ReleaseGovernanceDecision(
        candidate_page_id=candidate_page_id,
        slug=slug,
        source_rollout_status=source_rollout_status,
        governance_status=governance_status,
        approval_status=resolved_approval_status,
        requires_human_approval=requires_human_approval,
        can_request_limited_activation=can_request_limited_activation,
        can_publish_publicly=can_publish_publicly,
        can_expand_live_sitemap=can_expand_live_sitemap,
        requires_rollback=requires_rollback,
        blocker_reasons=tuple(dict.fromkeys(_to_reason_tuple(blocker_reasons))),
        approval_requirements=tuple(dict.fromkeys(_to_reason_tuple(approval_requirements))),
        rollback_reasons=tuple(dict.fromkeys(_to_reason_tuple(rollback_reasons))),
        evidence_summary=evidence_summary,
        audit_events=tuple(dict.fromkeys(_to_reason_tuple(audit_events))),
        is_public=is_public,
        is_live_sitemap_included=is_live_sitemap_included,
        is_mass_publish=is_mass_publish,
    )
    return _decision_to_payload(decision)


def build_release_audit_record(
    decision: Mapping[str, Any],
    actor: str = "system",
    action: str = "evaluated",
    notes: str | None = None,
) -> dict[str, Any]:
    payload = dict(decision or {})
    candidate_page_id = _norm_text(payload.get("candidate_page_id") or "candidate-page-unknown")
    slug = _norm_text(payload.get("slug"))
    governance_status = _norm_text(payload.get("governance_status"))
    approval_status = _norm_text(payload.get("approval_status"))
    actor_text = _norm_text(actor) or "system"
    action_text = _norm_text(action) or "evaluated"
    normalized_notes = _norm_text(notes) or None

    event_signature = (
        f"{candidate_page_id}|{slug}|{governance_status}|{approval_status}|"
        f"{actor_text}|{action_text}|{normalized_notes or ''}"
    )
    audit_record = ReleaseAuditRecord(
        audit_id=f"step11-audit-{candidate_page_id}",
        candidate_page_id=candidate_page_id,
        slug=slug,
        actor=actor_text,
        action=action_text,
        governance_status=governance_status,
        approval_status=approval_status,
        requires_human_approval=_as_bool(payload.get("requires_human_approval"), default=False),
        requires_rollback=_as_bool(payload.get("requires_rollback"), default=False),
        notes=normalized_notes,
        event_signature=event_signature,
    )
    return _audit_to_payload(audit_record)


def evaluate_release_governance_batch(
    rollout_decisions: Iterable[Mapping[str, Any]],
    approval_status_by_candidate: Mapping[str, ReleaseApprovalStatus | str] | None = None,
    policy: ReleaseGovernancePolicy | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    status_lookup = dict(approval_status_by_candidate or {})
    source_items = [dict(item) for item in rollout_decisions]
    ordered = sorted(
        source_items,
        key=lambda item: (_norm_text(item.get("candidate_page_id")), _norm_text(item.get("slug"))),
    )

    decisions: list[ReleaseGovernanceDecision] = []
    audit_records: list[ReleaseAuditRecord] = []
    for item in ordered:
        candidate_page_id = _norm_text(item.get("candidate_page_id"))
        explicit_approval_status = status_lookup.get(candidate_page_id, item.get("approval_status"))
        payload = evaluate_release_governance_decision(
            item,
            approval_status=explicit_approval_status,
            policy=resolved_policy,
        )
        decision = ReleaseGovernanceDecision(
            candidate_page_id=payload["candidate_page_id"],
            slug=payload["slug"],
            source_rollout_status=payload["source_rollout_status"],
            governance_status=GovernanceDecisionStatus(payload["governance_status"]),
            approval_status=ReleaseApprovalStatus(payload["approval_status"]),
            requires_human_approval=bool(payload["requires_human_approval"]),
            can_request_limited_activation=bool(payload["can_request_limited_activation"]),
            can_publish_publicly=bool(payload["can_publish_publicly"]),
            can_expand_live_sitemap=bool(payload["can_expand_live_sitemap"]),
            requires_rollback=bool(payload["requires_rollback"]),
            blocker_reasons=tuple(payload["blocker_reasons"]),
            approval_requirements=tuple(payload["approval_requirements"]),
            rollback_reasons=tuple(payload["rollback_reasons"]),
            evidence_summary=dict(payload["evidence_summary"]),
            audit_events=tuple(payload["audit_events"]),
            is_public=bool(payload["is_public"]),
            is_live_sitemap_included=bool(payload["is_live_sitemap_included"]),
            is_mass_publish=bool(payload["is_mass_publish"]),
        )
        decisions.append(decision)
        audit_payload = build_release_audit_record(payload)
        audit_records.append(
            ReleaseAuditRecord(
                audit_id=audit_payload["audit_id"],
                candidate_page_id=audit_payload["candidate_page_id"],
                slug=audit_payload["slug"],
                actor=audit_payload["actor"],
                action=audit_payload["action"],
                governance_status=audit_payload["governance_status"],
                approval_status=audit_payload["approval_status"],
                requires_human_approval=bool(audit_payload["requires_human_approval"]),
                requires_rollback=bool(audit_payload["requires_rollback"]),
                notes=audit_payload["notes"],
                event_signature=audit_payload["event_signature"],
            )
        )

    status_counts = _count_by_status(decisions)
    approval_status_counts = _count_by_approval_status(decisions)
    blocker_counts = _count_reasons(decisions, "blocker_reasons")
    rollback_counts = _count_reasons(decisions, "rollback_reasons")

    approval_ready_count = status_counts.get(GovernanceDecisionStatus.approval_ready.value, 0)
    approval_required_count = status_counts.get(GovernanceDecisionStatus.approval_required.value, 0)
    blocked_count = status_counts.get(GovernanceDecisionStatus.blocked.value, 0)
    rollback_required_count = status_counts.get(GovernanceDecisionStatus.rollback_required.value, 0)
    rejected_count = status_counts.get(GovernanceDecisionStatus.rejected.value, 0)
    pending_human_approval_count = approval_status_counts.get(ReleaseApprovalStatus.pending_human_approval.value, 0)
    approved_count = approval_status_counts.get(ReleaseApprovalStatus.approved.value, 0)
    total_records = len(decisions)

    can_move_to_real_provider_activation_review = bool(
        total_records > 0
        and approval_ready_count == total_records
        and blocked_count == 0
        and rollback_required_count == 0
        and rejected_count == 0
        and approved_count == total_records
        and all(item.can_request_limited_activation for item in decisions)
        and all(not item.can_publish_publicly for item in decisions)
        and all(not item.can_expand_live_sitemap for item in decisions)
        and all(not item.is_public for item in decisions)
        and all(not item.is_live_sitemap_included for item in decisions)
        and all(not item.is_mass_publish for item in decisions)
    )

    result = ReleaseGovernanceBatchResult(
        total_records=total_records,
        approval_ready_count=approval_ready_count,
        approval_required_count=approval_required_count,
        blocked_count=blocked_count,
        rollback_required_count=rollback_required_count,
        rejected_count=rejected_count,
        pending_human_approval_count=pending_human_approval_count,
        approved_count=approved_count,
        status_counts=status_counts,
        approval_status_counts=approval_status_counts,
        blocker_counts=blocker_counts,
        rollback_counts=rollback_counts,
        can_move_to_real_provider_activation_review=can_move_to_real_provider_activation_review,
        decisions=tuple(decisions),
        audit_records=tuple(audit_records),
    )
    output = asdict(result)
    output["decisions"] = [_decision_to_payload(item) for item in result.decisions]
    output["audit_records"] = [_audit_to_payload(item) for item in result.audit_records]
    return output
