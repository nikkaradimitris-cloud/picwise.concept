# PickWise Step 13: Human Activation Review / Real Provider Batch Approval

## Purpose

Step 13 adds a deterministic human activation review workflow for real provider batches after Step 12 pilot closure.

This step does not publish pages, does not expand live sitemap state, and does not move candidate pages into public routes. It only prepares and evaluates human approval packets.

## Why Human Approval Is Required

Step 13 requires explicit operator action because automated pilot readiness is not equivalent to release authorization. Human review confirms:

- Step 12 pilot is truly review-eligible (`pilot_ready` and requestable).
- Governance signals are in a safe state.
- Rollback simulation passes before any future activation phase.
- Public safety locks remain enforced.

Approval is never assumed by default.

## Review Packet Evidence

`HumanActivationReviewPacket` includes:

- packet identity and provider targeting (`review_packet_id`, provider, market, locale)
- pilot state and eligibility (`pilot_status`, `can_request_human_activation_review`)
- governance readiness signal (`governance_status`, `approval_ready_count`)
- rollback readiness (`rollback_drill_status`)
- evidence and operational checks (`evidence_summary`, `required_operator_checks`)
- blockers and remediation list (`blocker_reasons`, `remediation_actions`)
- hard safety locks
  - `can_publish_publicly = false`
  - `can_expand_live_sitemap = false`
  - `is_mass_publish = false`

## Human Actions and Outcomes

`HumanApprovalAction` is explicit:

- `approve`
- `reject`
- `hold`
- `request_remediation`

Decision outcomes (`HumanActivationDecisionStatus`):

- `activation_review_ready`
- `activation_approved_for_next_phase`
- `activation_rejected`
- `activation_hold_manual_review`
- `activation_blocked`

Rules:

- only review-eligible Step 12 packets can become review-ready
- missing action never auto-approves
- `approve` can pass only when blockers are empty and rollback simulation passes
- `reject` always produces `activation_rejected`
- `hold` and `request_remediation` produce manual hold outcomes
- blockers force `activation_blocked` unless operator explicitly rejects

## Rollback Simulation

`simulate_human_activation_rollback()` verifies rollback preconditions for each packet. The simulation is deterministic and checks:

- rollback drill completion signal
- dry-run only mode remains true
- no public/sitemap/mass-publish lock violations

Any failure blocks approval in Step 13.

## Audit Record Format

Each decision creates deterministic `HumanActivationAuditRecord` items with:

- `audit_id`
- `review_packet_id`
- `decision_id`
- `actor`
- `action`
- `decision_status`
- `operator_action`
- `reason`
- `event_signature`

This provides consistent traceability for human activation decisions.

## Why Step 13 Still Does Not Publish/Index/Sitemap Anything

Step 13 is review and control logic only. Decision outputs hard-lock:

- `can_publish_publicly = false`
- `can_expand_live_sitemap = false`
- `is_public = false`
- `is_live_sitemap_included = false`
- `is_mass_publish = false`

No route exposure, no sitemap mutation, and no public activation occurs here.

## Next Phase After Step 13

After Step 13 is closed, the next phase should implement a tightly scoped operator-supervised activation execution stage that consumes only explicitly approved Step 13 decisions and keeps existing governance and non-public safety gates intact until separate release criteria are satisfied.
