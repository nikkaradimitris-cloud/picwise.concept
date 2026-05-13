# PickWise Step 11: Release Governance and Human Approval

## Purpose

Step 11 introduces a deterministic governance and approval protocol for any movement from Step 10 controlled rollout outputs toward real provider activation review. This step exists to enforce human decision points, auditability, and rollback readiness before any operational activation workflow can be considered.

This step does **not** publish pages, does **not** connect live provider credentials, does **not** expand the live sitemap, and does **not** wire candidate pages into public `/best` routes.

## Why Step 11 Exists After the 10-Step Roadmap

Step 10 closes controlled rollout readiness as a policy stage. Step 11 separates readiness from activation by introducing formal governance contracts:

- Step 10 asks whether a record is rollout-ready under controlled policy.
- Step 11 asks whether that record can be considered for real provider activation review under explicit human approval.

This prevents accidental or inferred activation and keeps release movement auditable and reversible.

## Governance Contracts

Step 11 adds these contract types:

- `GovernanceDecisionStatus`
  - `approval_ready`
  - `approval_required`
  - `blocked`
  - `rollback_required`
  - `rejected`
- `ReleaseApprovalStatus`
  - `not_requested`
  - `pending_human_approval`
  - `approved`
  - `rejected`
  - `rollback_approved`
- `ReleaseGovernancePolicy`
- `ReleaseGovernanceDecision`
- `ReleaseGovernanceBatchResult`
- `ReleaseAuditRecord`

## What Requires Human Approval

Any record that is `limited_rollout_ready` at Step 10 still requires explicit human approval in Step 11. Approval is never inferred from prior status.

The human approval status must always be explicit and can only be one of:

- `not_requested`
- `pending_human_approval`
- `approved`
- `rejected`
- `rollback_approved`

## Evidence Required Before Activation Review

Step 11 decision evidence summarizes the signals used to allow or block activation review, including:

- source rollout status and rollback flags
- source non-public safety flags (`is_public`, `is_live_sitemap_included`, `is_mass_publish`)
- live provider and credential safety flags
- explicit-approval presence
- blocker and rollback signals derived from upstream reasons

A record is only considered `approval_ready` when:

1. Source rollout status is `limited_rollout_ready`.
2. No blocker or rollback signals are present.
3. Approval status is explicitly `approved`.
4. Step 11 safety constraints remain intact (non-public, non-sitemap, non-mass-publish, no credentials/live provider connection).

## Automatic Blocks and Rollback Rules

Step 11 automatically blocks or rolls back on these conditions:

- **Blocked**
  - source rollout status is blocked (`scale_blocked`) or unsupported
  - blocker signals appear in reason sets
  - any source state implies public/sitemap/mass-publish exposure
  - any source state implies credentials or live provider connection
- **Rollback required**
  - source rollout status is `rollback_required`
  - source requires rollback
  - rollback signals/tokens are present
  - approval status is `rollback_approved`
- **Rejected**
  - approval status is explicitly `rejected`

## Audit Record Format

Each governance decision emits deterministic audit data:

- `audit_id`
- `candidate_page_id`
- `slug`
- `actor`
- `action`
- `governance_status`
- `approval_status`
- `requires_human_approval`
- `requires_rollback`
- `notes`
- `event_signature`

The `event_signature` is deterministic and built from stable decision and actor/action fields so repeated evaluations are reproducible.

## Batch Governance Outcome

Batch evaluation reports:

- total/status counts
- approval status counts
- blocker and rollback reason counts
- decision list
- audit record list
- `can_move_to_real_provider_activation_review`

`can_move_to_real_provider_activation_review` is true only when every record is `approval_ready`, explicitly `approved`, and all Step 11 non-public safety guarantees remain true.

## Why Step 11 Still Does Not Publish or Index

Step 11 hard-locks the following fields in governance decisions:

- `can_publish_publicly = false`
- `can_expand_live_sitemap = false`
- `is_public = false`
- `is_live_sitemap_included = false`
- `is_mass_publish = false`

This keeps Step 11 strictly governance-only and prevents operational publishing side effects.

## Next Phase After Step 11

The next phase should be a controlled real-provider activation pilot protocol that:

1. consumes only Step 11 `approval_ready` + explicitly `approved` records,
2. executes under operator-run runbooks with rollback drills,
3. maintains non-public exposure by default unless a separate publish-governance step explicitly approves it,
4. logs provider activation actions using the same deterministic audit standards.
