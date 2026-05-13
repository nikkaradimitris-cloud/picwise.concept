# PickWise Roadmap Step 9 - Improvement / Promotion Policy

## Purpose

Roadmap Step 9 introduces a deterministic policy layer that evaluates Step 8 observation summaries and decides controlled next actions for each MVP candidate page.

This step is policy-only. It does not publish pages, does not expand the live sitemap, does not wire candidate pages into `/best`, and does not introduce external analytics/provider API dependencies or credentials.

## Step 8 -> Step 9 Input Contract

Step 9 consumes Step 8 `MVPPageObservationSummary`-style records:

- `status` (`observation_ready`, `needs_more_data`, `hold_manual_review`, `blocked`)
- `promotion_ready`
- preview/outbound evidence counts
- preview/outbound error counts
- manual review and blocker counts
- controlled/reversible and live-mvp readiness signals

Step 9 maps each input into a promotion decision without side effects.

## Promotion Decision Statuses

Step 9 supports the following deterministic statuses:

- `promoted_to_limited_exposure`
- `keep_controlled`
- `hold_manual_review`
- `reject_from_promotion`
- `rollback_required`
- `needs_more_observation`

## Decision Rules

- Only Step 8 `observation_ready` + `promotion_ready` pages can become `promoted_to_limited_exposure`.
- Step 8 `needs_more_data` maps to `needs_more_observation`.
- Step 8 hold/manual-review signals map to `hold_manual_review`.
- Step 8 blocked/blocker signals map to `reject_from_promotion` or `rollback_required`.
- Any blocker event forces reject/rollback outcomes.
- Outbound/preview error thresholds force hold or rollback.
- Missing preview/outbound evidence forces `needs_more_observation`.
- Non-live-ready or non-controlled records cannot be promoted.
- Every decision remains reversible and controlled.

## Limited Exposure Is Not Mass Publish

`promoted_to_limited_exposure` is a policy status only. It does not:

- publish a page,
- change indexability,
- modify runtime route wiring,
- replace existing `/best` routes,
- or add entries to live sitemap output.

## Sitemap Candidate Flag Clarification

`can_expand_sitemap_candidate` is only a policy flag that indicates eligibility for a future step decision. It is not live sitemap inclusion and does not write sitemap files.

`is_live_sitemap_included` is fixed `false` in Step 9 decisions.

## Rollback / Hold / Reject Behavior

- `hold_manual_review` is used when manual review events or non-severe error thresholds appear.
- `reject_from_promotion` is used for blocked states with no rollback trigger.
- `rollback_required` is used for severe error trends or rollback-indicator blockers.

## Step 9 Closure Evidence

Step 9 can be considered closed when:

- policy contracts are implemented and deterministic,
- mixed-batch tests prove all expected status branches,
- selected clean cohort tests prove promotion-ready pages can all reach `promoted_to_limited_exposure`,
- no public exposure/sitemap/route side effects are introduced,
- no fabricated revenue/conversion/search-volume/product/link metrics are introduced.

## Step 10 Handoff

Step 10 should consume Step 9 decisions and execute tightly controlled operational actions (if approved), while preserving:

- no mass publish,
- no automatic route replacement,
- no automatic live sitemap expansion,
- strict rollback path and manual review controls.
