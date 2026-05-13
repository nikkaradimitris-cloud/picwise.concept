# PickWise Roadmap Step 10 - Scale / Controlled Rollout

## Purpose

Roadmap Step 10 adds a deterministic controlled rollout policy layer on top of Step 9 promotion decisions.

This step does not publish pages, does not expand the live sitemap, does not wire candidate pages into `/best`, and does not mass publish.

## Step 9 -> Step 10 Policy Flow

Step 10 consumes Step 9 `PromotionDecision`-style records and maps each record into a rollout-control status.

The input signal for limited rollout readiness is only `promoted_to_limited_exposure`.

All other Step 9 outcomes remain constrained:

- `keep_controlled` -> `keep_in_preview`
- `hold_manual_review` -> `hold_manual_review`
- `reject_from_promotion` -> `scale_blocked`
- `rollback_required` -> `rollback_required`
- `needs_more_observation` -> `needs_more_observation`

## Controlled Rollout Statuses

Step 10 statuses:

- `limited_rollout_ready`
- `keep_in_preview`
- `hold_manual_review`
- `rollback_required`
- `scale_blocked`
- `needs_more_observation`

Step 10 rollout tiers:

- `none`
- `preview_only`
- `limited`
- `expanded_candidate`

## Limited Rollout Is Not Mass Publish

`limited_rollout_ready` is an internal policy outcome, not a live publish action.

Step 10 explicitly keeps:

- `is_public = false`
- `is_live_sitemap_included = false`
- `is_mass_publish = false`

## Sitemap Candidate Flag Clarification

`can_be_considered_for_sitemap_later` is a policy-only eligibility flag for future approval stages.

It does not write sitemap files and does not include pages in the live sitemap.

## Rollback, Hold, and Block Rules

- Any rollback signal forces `rollback_required`.
- Any blocker signal forces `scale_blocked` or `hold_manual_review`.
- `rollback_required` remains reversible by design and does not trigger live publish.
- Manual review outcomes remain in controlled preview workflows only.

## Rollout Cap Behavior

Step 10 applies `max_limited_rollout_records` to cap how many records can be `limited_rollout_ready` in a batch.

When promoted records exceed the cap, overflow records are deterministically kept in preview (`keep_in_preview`) with explicit review reasons.

This preserves controlled pacing and reversibility while preventing accidental scale jumps.

## Evidence Required To Close Step 10

Step 10 can close when:

- mixed-batch tests verify all status mappings and forcing rules,
- rollout cap behavior is deterministic and enforced,
- selected clean rollout cohort reaches only `limited_rollout_ready`,
- no hold/rollback/blocked outcomes exist in selected clean closure batch,
- all outputs remain policy-only (`is_public`, live sitemap, and mass publish all false),
- no fabricated impressions/clicks/conversions/revenue/search-volume/products/prices/links are introduced,
- no route wiring, naming, or sitemap behavior changes are introduced.

## What Is Allowed After Step 10 Closure

After closure, the project has a deterministic policy contract for controlled rollout eligibility and reversible scale gating.

This allows preparing explicit next-stage approval packages without auto-publishing.

## What Still Requires Explicit Future Approval

The following remain out of scope until future explicit approval:

- real public publishing of new pages,
- live sitemap inclusion changes,
- `/best` route expansion or replacement,
- mass publish or automatic scale expansion,
- live external analytics/provider API integrations with credentials.
