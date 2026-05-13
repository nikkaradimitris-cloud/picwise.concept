from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping


class HumanActivationDecisionStatus(str, Enum):
    activation_review_ready = "activation_review_ready"
    activation_approved_for_next_phase = "activation_approved_for_next_phase"
    activation_rejected = "activation_rejected"
    activation_hold_manual_review = "activation_hold_manual_review"
    activation_blocked = "activation_blocked"


class HumanApprovalAction(str, Enum):
    approve = "approve"
    reject = "reject"
    hold = "hold"
    request_remediation = "request_remediation"


@dataclass(frozen=True)
class HumanActivationReviewPacket:
    review_packet_id: str
    provider_name: str
    target_market: str
    target_locale: str
    pilot_status: str
    can_request_human_activation_review: bool
    governance_status: str
    approval_ready_count: int
    rollback_drill_status: str
    dry_run_only: bool
    evidence_summary: Mapping[str, Any]
    required_operator_checks: tuple[str, ...]
    blocker_reasons: tuple[str, ...]
    remediation_actions: tuple[str, ...]
    can_publish_publicly: bool
    can_expand_live_sitemap: bool
    is_mass_publish: bool


@dataclass(frozen=True)
class HumanActivationRollbackSimulation:
    simulation_id: str
    review_packet_id: str
    rollback_drill_status: str
    passed: bool
    failure_reasons: tuple[str, ...]
    confirmation_steps: tuple[str, ...]


@dataclass(frozen=True)
class HumanActivationAuditRecord:
    audit_id: str
    review_packet_id: str
    decision_id: str
    actor: str
    action: str
    decision_status: str
    operator_action: str
    reason: str
    event_signature: str


@dataclass(frozen=True)
class HumanActivationDecision:
    decision_id: str
    review_packet_id: str
    decision_status: HumanActivationDecisionStatus
    operator_action: str
    operator_id: str | None
    decision_timestamp: str | None
    reason: str
    blocker_reasons: tuple[str, ...]
    remediation_actions: tuple[str, ...]
    rollback_simulation: HumanActivationRollbackSimulation
    audit_records: tuple[HumanActivationAuditRecord, ...]
    can_move_to_next_phase: bool
    can_publish_publicly: bool
    can_expand_live_sitemap: bool
    is_public: bool
    is_live_sitemap_included: bool
    is_mass_publish: bool


@dataclass(frozen=True)
class HumanActivationBatchResult:
    total_packets: int
    activation_review_ready_count: int
    activation_approved_for_next_phase_count: int
    activation_rejected_count: int
    activation_hold_manual_review_count: int
    activation_blocked_count: int
    status_counts: dict[str, int]
    blocker_counts: dict[str, int]
    remediation_counts: dict[str, int]
    rollback_simulation_pass_count: int
    can_move_to_next_phase: bool
    decisions: tuple[HumanActivationDecision, ...]
    audit_records: tuple[HumanActivationAuditRecord, ...]


@dataclass(frozen=True)
class HumanActivationReviewPolicy:
    require_pilot_status_for_review_ready: str = "pilot_ready"
    require_explicit_operator_action_for_approval: bool = True
    force_hold_when_missing_action: bool = False
    force_rollback_failure_review_packet_ids: tuple[str, ...] = ()
    require_dry_run_only: bool = True
    require_non_public_locks: bool = True


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


def _policy_from_input(policy: HumanActivationReviewPolicy | Mapping[str, Any] | None) -> HumanActivationReviewPolicy:
    if isinstance(policy, HumanActivationReviewPolicy):
        return policy
    if policy is None:
        return HumanActivationReviewPolicy()
    payload = dict(policy)
    return HumanActivationReviewPolicy(
        require_pilot_status_for_review_ready=_norm_text(payload.get("require_pilot_status_for_review_ready")) or "pilot_ready",
        require_explicit_operator_action_for_approval=bool(
            payload.get("require_explicit_operator_action_for_approval", True)
        ),
        force_hold_when_missing_action=bool(payload.get("force_hold_when_missing_action", False)),
        force_rollback_failure_review_packet_ids=tuple(
            _norm_text(item)
            for item in payload.get("force_rollback_failure_review_packet_ids", ())
            if _norm_text(item)
        ),
        require_dry_run_only=bool(payload.get("require_dry_run_only", True)),
        require_non_public_locks=bool(payload.get("require_non_public_locks", True)),
    )


def _governance_status_from_batch(governance_batch: Mapping[str, Any] | None) -> str:
    if not isinstance(governance_batch, Mapping):
        return "governance_not_provided"
    blocked_count = _as_int(governance_batch.get("blocked_count"))
    rollback_count = _as_int(governance_batch.get("rollback_required_count"))
    rejected_count = _as_int(governance_batch.get("rejected_count"))
    approval_ready_count = _as_int(governance_batch.get("approval_ready_count"))
    total_records = _as_int(governance_batch.get("total_records"))
    can_move = _as_bool(governance_batch.get("can_move_to_real_provider_activation_review"))

    if blocked_count > 0 or rollback_count > 0 or rejected_count > 0:
        return "governance_blocked"
    if can_move:
        return "governance_approval_ready"
    if total_records > 0 and approval_ready_count == total_records:
        return "governance_approval_ready"
    if approval_ready_count > 0:
        return "governance_partially_ready"
    return "governance_pending"


def _to_review_packet_payload(review_packet: HumanActivationReviewPacket) -> dict[str, Any]:
    payload = asdict(review_packet)
    payload["evidence_summary"] = dict(review_packet.evidence_summary)
    return payload


def _to_rollback_payload(rollback_simulation: HumanActivationRollbackSimulation) -> dict[str, Any]:
    return asdict(rollback_simulation)


def _to_audit_payload(audit_record: HumanActivationAuditRecord) -> dict[str, Any]:
    return asdict(audit_record)


def _to_decision_payload(decision: HumanActivationDecision) -> dict[str, Any]:
    payload = asdict(decision)
    payload["decision_status"] = decision.decision_status.value
    payload["rollback_simulation"] = _to_rollback_payload(decision.rollback_simulation)
    payload["audit_records"] = [_to_audit_payload(item) for item in decision.audit_records]
    return payload


def _to_review_packet(input_packet: HumanActivationReviewPacket | Mapping[str, Any]) -> HumanActivationReviewPacket:
    if isinstance(input_packet, HumanActivationReviewPacket):
        return input_packet
    payload = dict(input_packet or {})
    return HumanActivationReviewPacket(
        review_packet_id=_norm_text(payload.get("review_packet_id")) or "step13-review-packet-unknown",
        provider_name=_norm_text(payload.get("provider_name")) or "provider-unknown",
        target_market=_norm_text(payload.get("target_market")).upper(),
        target_locale=_norm_text(payload.get("target_locale")),
        pilot_status=_norm_text(payload.get("pilot_status")) or "pilot_unknown",
        can_request_human_activation_review=_as_bool(payload.get("can_request_human_activation_review"), default=False),
        governance_status=_norm_text(payload.get("governance_status")) or "governance_not_provided",
        approval_ready_count=_as_int(payload.get("approval_ready_count")),
        rollback_drill_status=_norm_text(payload.get("rollback_drill_status")) or "rollback_drill_unknown",
        dry_run_only=_as_bool(payload.get("dry_run_only"), default=False),
        evidence_summary=dict(payload.get("evidence_summary") or {}),
        required_operator_checks=_to_reason_tuple(payload.get("required_operator_checks")),
        blocker_reasons=_to_reason_tuple(payload.get("blocker_reasons")),
        remediation_actions=_to_reason_tuple(payload.get("remediation_actions")),
        can_publish_publicly=False,
        can_expand_live_sitemap=False,
        is_mass_publish=False,
    )


def build_human_activation_review_packet(
    pilot_result: Mapping[str, Any],
    governance_batch: Mapping[str, Any] | None = None,
    rollback_drill: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pilot = dict(pilot_result or {})
    provider_name = _norm_text(pilot.get("provider_name")) or "provider-unknown"
    target_market = _norm_text(pilot.get("target_market")).upper()
    target_locale = _norm_text(pilot.get("target_locale"))
    pilot_status = _norm_text(pilot.get("pilot_status")) or "pilot_unknown"
    dry_run_only = _as_bool(pilot.get("dry_run_only"), default=False)
    can_request_human_activation_review = _as_bool(
        pilot.get("can_request_human_activation_review"),
        default=False,
    )

    governance_status = _governance_status_from_batch(governance_batch)
    approval_ready_count = _as_int(
        (governance_batch or {}).get("approval_ready_count"),
        default=_as_int(pilot.get("governance_approval_ready_count")),
    )
    rollback_payload = dict(rollback_drill or pilot.get("rollback_drill") or {})
    rollback_drill_status = "rollback_drill_passed" if _as_bool(rollback_payload.get("is_complete")) else "rollback_drill_failed"

    blocker_reasons = list(_to_reason_tuple(pilot.get("blocker_reasons")))
    remediation_actions = list(_to_reason_tuple(pilot.get("remediation_actions")))
    if pilot_status != "pilot_ready":
        blocker_reasons.append("pilot_status_must_be_pilot_ready")
    if not can_request_human_activation_review:
        blocker_reasons.append("pilot_not_eligible_for_human_activation_review")
    if governance_status in {"governance_blocked", "governance_pending"}:
        blocker_reasons.append("governance_not_ready_for_human_activation_review")
    if rollback_drill_status != "rollback_drill_passed":
        blocker_reasons.append("rollback_drill_not_complete")
    if not dry_run_only:
        blocker_reasons.append("dry_run_only_must_remain_true")

    required_operator_checks = (
        "confirm_pilot_ready_and_human_review_eligibility",
        "confirm_governance_approval_ready_inputs",
        "confirm_rollback_simulation_pass_before_approval",
        "confirm_no_public_publish_or_sitemap_expansion",
        "record_explicit_operator_action_and_reason",
    )
    evidence_summary = {
        "pilot_status": pilot_status,
        "governance_status": governance_status,
        "approval_ready_count": approval_ready_count,
        "governance_approval_ready_count_from_pilot": _as_int(pilot.get("governance_approval_ready_count")),
        "feed_rows_total": _as_int(pilot.get("feed_rows_total")),
        "candidate_pages_built": _as_int(pilot.get("candidate_pages_built")),
        "limited_rollout_ready_count": _as_int(pilot.get("limited_rollout_ready_count")),
        "dry_run_only": dry_run_only,
        "rollback_drill_status": rollback_drill_status,
        "can_publish_publicly": False,
        "can_expand_live_sitemap": False,
        "is_mass_publish": False,
    }

    review_packet = HumanActivationReviewPacket(
        review_packet_id=(
            "step13-review-"
            f"{provider_name.lower().replace(' ', '-') or 'provider'}-"
            f"{target_market.lower() or 'market'}-"
            f"{target_locale.lower().replace(' ', '-') or 'locale'}"
        ),
        provider_name=provider_name,
        target_market=target_market,
        target_locale=target_locale,
        pilot_status=pilot_status,
        can_request_human_activation_review=can_request_human_activation_review,
        governance_status=governance_status,
        approval_ready_count=approval_ready_count,
        rollback_drill_status=rollback_drill_status,
        dry_run_only=dry_run_only,
        evidence_summary=evidence_summary,
        required_operator_checks=required_operator_checks,
        blocker_reasons=tuple(dict.fromkeys(_to_reason_tuple(blocker_reasons))),
        remediation_actions=tuple(dict.fromkeys(_to_reason_tuple(remediation_actions))),
        can_publish_publicly=False,
        can_expand_live_sitemap=False,
        is_mass_publish=False,
    )
    return _to_review_packet_payload(review_packet)


def simulate_human_activation_rollback(
    review_packet: HumanActivationReviewPacket | Mapping[str, Any],
    policy: HumanActivationReviewPolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = _to_review_packet(review_packet)
    resolved_policy = _policy_from_input(policy)
    failure_reasons: list[str] = []

    if packet.rollback_drill_status != "rollback_drill_passed":
        failure_reasons.append("rollback_drill_status_not_passed")
    if resolved_policy.require_dry_run_only and not packet.dry_run_only:
        failure_reasons.append("dry_run_only_must_remain_true")
    if resolved_policy.require_non_public_locks and (
        packet.can_publish_publicly or packet.can_expand_live_sitemap or packet.is_mass_publish
    ):
        failure_reasons.append("public_or_sitemap_or_mass_publish_lock_violation")
    if packet.review_packet_id in set(resolved_policy.force_rollback_failure_review_packet_ids):
        failure_reasons.append("policy_forced_rollback_simulation_failure")

    rollback = HumanActivationRollbackSimulation(
        simulation_id=f"step13-rollback-simulation-{packet.review_packet_id}",
        review_packet_id=packet.review_packet_id,
        rollback_drill_status=packet.rollback_drill_status,
        passed=len(failure_reasons) == 0,
        failure_reasons=tuple(dict.fromkeys(_to_reason_tuple(failure_reasons))),
        confirmation_steps=(
            "confirm_non_public_locks",
            "confirm_dry_run_only_mode",
            "confirm_operator_can_revert_to_previous_batch",
            "confirm_remediation_log_is_preserved",
        ),
    )
    return _to_rollback_payload(rollback)


def evaluate_human_activation_decision(
    review_packet: HumanActivationReviewPacket | Mapping[str, Any],
    operator_action: HumanApprovalAction | str | None = None,
    operator_id: str | None = None,
    reason: str | None = None,
    policy: HumanActivationReviewPolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    packet = _to_review_packet(review_packet)
    resolved_policy = _policy_from_input(policy)
    action_text = _norm_text(operator_action)
    if action_text not in {item.value for item in HumanApprovalAction}:
        action_text = ""

    normalized_operator_id = _norm_text(operator_id) or None
    normalized_reason = _norm_text(reason) or "operator_reason_not_provided"
    initial_blockers = list(_to_reason_tuple(packet.blocker_reasons))
    remediation_actions = list(_to_reason_tuple(packet.remediation_actions))

    is_review_ready_input = bool(
        packet.pilot_status == resolved_policy.require_pilot_status_for_review_ready
        and packet.can_request_human_activation_review
    )
    if not is_review_ready_input and "packet_not_review_ready_for_step13" not in initial_blockers:
        initial_blockers.append("packet_not_review_ready_for_step13")

    rollback_simulation_payload = simulate_human_activation_rollback(packet, policy=resolved_policy)
    rollback_simulation = HumanActivationRollbackSimulation(
        simulation_id=rollback_simulation_payload["simulation_id"],
        review_packet_id=rollback_simulation_payload["review_packet_id"],
        rollback_drill_status=rollback_simulation_payload["rollback_drill_status"],
        passed=bool(rollback_simulation_payload["passed"]),
        failure_reasons=tuple(rollback_simulation_payload["failure_reasons"]),
        confirmation_steps=tuple(rollback_simulation_payload["confirmation_steps"]),
    )
    if not rollback_simulation.passed:
        initial_blockers.extend(list(rollback_simulation.failure_reasons))

    decision_status = HumanActivationDecisionStatus.activation_review_ready

    if not action_text:
        if initial_blockers:
            decision_status = HumanActivationDecisionStatus.activation_blocked
        elif resolved_policy.force_hold_when_missing_action:
            decision_status = HumanActivationDecisionStatus.activation_hold_manual_review
        else:
            decision_status = HumanActivationDecisionStatus.activation_review_ready
    elif action_text == HumanApprovalAction.reject.value:
        decision_status = HumanActivationDecisionStatus.activation_rejected
    elif action_text == HumanApprovalAction.hold.value:
        decision_status = HumanActivationDecisionStatus.activation_hold_manual_review
    elif action_text == HumanApprovalAction.request_remediation.value:
        decision_status = HumanActivationDecisionStatus.activation_hold_manual_review
        remediation_actions.append("operator_requested_remediation")
    elif action_text == HumanApprovalAction.approve.value:
        can_approve = bool(is_review_ready_input and not initial_blockers and rollback_simulation.passed)
        if can_approve:
            decision_status = HumanActivationDecisionStatus.activation_approved_for_next_phase
        else:
            decision_status = HumanActivationDecisionStatus.activation_blocked
            if not rollback_simulation.passed:
                remediation_actions.append("resolve_rollback_simulation_failures")
            if initial_blockers:
                remediation_actions.append("clear_step13_blockers_before_approval")

    if action_text != HumanApprovalAction.reject.value and initial_blockers:
        decision_status = HumanActivationDecisionStatus.activation_blocked

    can_move_to_next_phase = decision_status == HumanActivationDecisionStatus.activation_approved_for_next_phase
    operator_action_value = action_text or "none"
    decision_id = f"step13-decision-{packet.review_packet_id}-{operator_action_value}"

    audit_inputs = (
        ("evaluated", f"packet_evaluated:{packet.review_packet_id}"),
        ("decided", f"decision_recorded:{decision_status.value}"),
    )
    audit_records: list[HumanActivationAuditRecord] = []
    for idx, (action_name, action_reason) in enumerate(audit_inputs, start=1):
        event_signature = (
            f"{packet.review_packet_id}|{decision_id}|{action_name}|{decision_status.value}|"
            f"{operator_action_value}|{normalized_operator_id or 'operator-unknown'}|{normalized_reason}"
        )
        audit_records.append(
            HumanActivationAuditRecord(
                audit_id=f"step13-audit-{packet.review_packet_id}-{idx}",
                review_packet_id=packet.review_packet_id,
                decision_id=decision_id,
                actor=normalized_operator_id or "system",
                action=action_name,
                decision_status=decision_status.value,
                operator_action=operator_action_value,
                reason=action_reason if normalized_reason == "operator_reason_not_provided" else normalized_reason,
                event_signature=event_signature,
            )
        )

    decision = HumanActivationDecision(
        decision_id=decision_id,
        review_packet_id=packet.review_packet_id,
        decision_status=decision_status,
        operator_action=operator_action_value,
        operator_id=normalized_operator_id,
        decision_timestamp=None,
        reason=normalized_reason,
        blocker_reasons=tuple(dict.fromkeys(_to_reason_tuple(initial_blockers))),
        remediation_actions=tuple(dict.fromkeys(_to_reason_tuple(remediation_actions))),
        rollback_simulation=rollback_simulation,
        audit_records=tuple(audit_records),
        can_move_to_next_phase=can_move_to_next_phase,
        can_publish_publicly=False,
        can_expand_live_sitemap=False,
        is_public=False,
        is_live_sitemap_included=False,
        is_mass_publish=False,
    )
    return _to_decision_payload(decision)


def _count_statuses(decisions: Iterable[HumanActivationDecision]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        key = decision.decision_status.value
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _count_reasons(decisions: Iterable[HumanActivationDecision], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        for reason in getattr(decision, attr):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def evaluate_human_activation_batch(
    review_packets: Iterable[HumanActivationReviewPacket | Mapping[str, Any]],
    operator_actions_by_packet: Mapping[str, Any] | None = None,
    policy: HumanActivationReviewPolicy | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_policy = _policy_from_input(policy)
    normalized_packets = [_to_review_packet(item) for item in review_packets]
    ordered_packets = sorted(
        normalized_packets,
        key=lambda item: (item.review_packet_id, item.provider_name, item.target_locale),
    )
    action_lookup = dict(operator_actions_by_packet or {})

    decisions: list[HumanActivationDecision] = []
    audit_records: list[HumanActivationAuditRecord] = []
    for packet in ordered_packets:
        action_payload = action_lookup.get(packet.review_packet_id)
        operator_action: str | None = None
        operator_id: str | None = None
        reason: str | None = None
        if isinstance(action_payload, Mapping):
            operator_action = _norm_text(action_payload.get("operator_action") or action_payload.get("action")) or None
            operator_id = _norm_text(action_payload.get("operator_id")) or None
            reason = _norm_text(action_payload.get("reason")) or None
        else:
            operator_action = _norm_text(action_payload) or None

        decision_payload = evaluate_human_activation_decision(
            packet,
            operator_action=operator_action,
            operator_id=operator_id,
            reason=reason,
            policy=resolved_policy,
        )
        decision = HumanActivationDecision(
            decision_id=decision_payload["decision_id"],
            review_packet_id=decision_payload["review_packet_id"],
            decision_status=HumanActivationDecisionStatus(decision_payload["decision_status"]),
            operator_action=decision_payload["operator_action"],
            operator_id=decision_payload["operator_id"],
            decision_timestamp=decision_payload["decision_timestamp"],
            reason=decision_payload["reason"],
            blocker_reasons=tuple(decision_payload["blocker_reasons"]),
            remediation_actions=tuple(decision_payload["remediation_actions"]),
            rollback_simulation=HumanActivationRollbackSimulation(
                simulation_id=decision_payload["rollback_simulation"]["simulation_id"],
                review_packet_id=decision_payload["rollback_simulation"]["review_packet_id"],
                rollback_drill_status=decision_payload["rollback_simulation"]["rollback_drill_status"],
                passed=bool(decision_payload["rollback_simulation"]["passed"]),
                failure_reasons=tuple(decision_payload["rollback_simulation"]["failure_reasons"]),
                confirmation_steps=tuple(decision_payload["rollback_simulation"]["confirmation_steps"]),
            ),
            audit_records=tuple(
                HumanActivationAuditRecord(
                    audit_id=item["audit_id"],
                    review_packet_id=item["review_packet_id"],
                    decision_id=item["decision_id"],
                    actor=item["actor"],
                    action=item["action"],
                    decision_status=item["decision_status"],
                    operator_action=item["operator_action"],
                    reason=item["reason"],
                    event_signature=item["event_signature"],
                )
                for item in decision_payload["audit_records"]
            ),
            can_move_to_next_phase=bool(decision_payload["can_move_to_next_phase"]),
            can_publish_publicly=bool(decision_payload["can_publish_publicly"]),
            can_expand_live_sitemap=bool(decision_payload["can_expand_live_sitemap"]),
            is_public=bool(decision_payload["is_public"]),
            is_live_sitemap_included=bool(decision_payload["is_live_sitemap_included"]),
            is_mass_publish=bool(decision_payload["is_mass_publish"]),
        )
        decisions.append(decision)
        audit_records.extend(list(decision.audit_records))

    status_counts = _count_statuses(decisions)
    blocker_counts = _count_reasons(decisions, "blocker_reasons")
    remediation_counts = _count_reasons(decisions, "remediation_actions")

    review_ready_count = status_counts.get(HumanActivationDecisionStatus.activation_review_ready.value, 0)
    approved_count = status_counts.get(HumanActivationDecisionStatus.activation_approved_for_next_phase.value, 0)
    rejected_count = status_counts.get(HumanActivationDecisionStatus.activation_rejected.value, 0)
    hold_count = status_counts.get(HumanActivationDecisionStatus.activation_hold_manual_review.value, 0)
    blocked_count = status_counts.get(HumanActivationDecisionStatus.activation_blocked.value, 0)
    rollback_simulation_pass_count = sum(1 for item in decisions if item.rollback_simulation.passed)
    total_packets = len(decisions)

    can_move_to_next_phase = bool(
        total_packets > 0
        and approved_count == total_packets
        and review_ready_count == 0
        and rejected_count == 0
        and hold_count == 0
        and blocked_count == 0
        and rollback_simulation_pass_count == total_packets
        and all(item.can_move_to_next_phase for item in decisions)
        and all(not item.can_publish_publicly for item in decisions)
        and all(not item.can_expand_live_sitemap for item in decisions)
        and all(not item.is_public for item in decisions)
        and all(not item.is_live_sitemap_included for item in decisions)
        and all(not item.is_mass_publish for item in decisions)
    )

    batch = HumanActivationBatchResult(
        total_packets=total_packets,
        activation_review_ready_count=review_ready_count,
        activation_approved_for_next_phase_count=approved_count,
        activation_rejected_count=rejected_count,
        activation_hold_manual_review_count=hold_count,
        activation_blocked_count=blocked_count,
        status_counts=status_counts,
        blocker_counts=blocker_counts,
        remediation_counts=remediation_counts,
        rollback_simulation_pass_count=rollback_simulation_pass_count,
        can_move_to_next_phase=can_move_to_next_phase,
        decisions=tuple(decisions),
        audit_records=tuple(audit_records),
    )
    payload = asdict(batch)
    payload["decisions"] = [_to_decision_payload(item) for item in batch.decisions]
    payload["audit_records"] = [_to_audit_payload(item) for item in batch.audit_records]
    return payload
