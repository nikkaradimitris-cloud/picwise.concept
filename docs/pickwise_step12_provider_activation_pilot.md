# PickWise Step 12: Operator-Run Real Provider Activation Pilot

## Purpose

Step 12 introduces an operator-run pilot framework that validates a **real local provider export package** through the already closed pipeline gates, strictly as a dry-run.

This step is designed to answer one question: can the provider package safely request human activation review, without any public publishing side effects?

## Why This Is Operator-Run

Step 12 is intentionally manual/operator-driven so every provider package is explicit, reviewable, and auditable before any activation request.

The operator provides local file paths and runs deterministic checks. No hidden fetches, no credential wiring, and no implicit data generation are allowed.

## Required Operator Inputs

The `ProviderActivationInputContract` requires:

- `provider_feed_export_file_path` (required)
- `trusted_seller_map_file_path` (optional, policy-controlled)
- `shipping_return_enrichment_map_path` (optional)
- `taxonomy_category_map_path` (optional)
- `keyword_cluster_batch_path` (optional in contract, required by default policy for page planning)
- `target_market`
- `target_locale`
- `dry_run_only = true`

## Pipeline Checks Included In Step 12

Step 12 dry-run evaluates the local package through the existing closed stages:

- Step 2 feed/provider readiness (`run_affiliate_feed_dry_run`)
- Step 3 locale logic (`evaluate_locale_product_eligibility`)
- Step 4 keyword cluster readiness (`validate_keyword_cluster_batch`)
- Step 5 candidate page planning (`build_candidate_page_batch`)
- Step 6 index candidate gate (`evaluate_candidate_index_batch`)
- Step 7 live MVP gate (`build_live_mvp_batch`)
- Step 8 observation contract (`summarize_mvp_observations`)
- Step 9 promotion policy (`evaluate_promotion_policy_batch`)
- Step 10 controlled rollout (`evaluate_controlled_rollout_batch`)
- Step 11 governance approval (`evaluate_release_governance_batch`)

## What Blocks The Pilot

Typical blocking reasons:

- missing feed export file
- `dry_run_only` is false
- unsupported or mismatched market/locale
- missing keyword cluster batch for page planning
- locale gate blocked candidates
- other hard gate blockers inherited from pipeline outcomes

## What Remediation Means

Remediation does not bypass gates. It means the operator must provide missing trusted local inputs (for example trusted seller maps, enrichment maps, observation evidence) and rerun the dry-run.

The pilot output includes deterministic `remediation_actions` and checklist remediation items.

## Human Activation Review Meaning

`can_request_human_activation_review = true` means:

- pilot reached `pilot_ready`
- governance approval-ready conditions are met
- public safety locks are still hard-false

It does **not** mean pages are published.

## Why Step 12 Still Does Not Publish/Index/Sitemap Anything

Step 12 hard-locks:

- `can_publish_publicly = false`
- `can_expand_live_sitemap = false`
- `is_mass_publish = false`

No route wiring, no sitemap mutation, and no public `/best` expansion are performed.

## Rollback Drill

Step 12 includes a deterministic rollback drill (`ProviderActivationRollbackDrill`) covering:

- stop pilot run
- revert local input package
- verify public locks remain unchanged
- log remediation evidence

Because this step is dry-run only, rollback is operationally safe and non-customer-impacting.

## Pilot Verdicts

Step 12 returns one of:

- `pilot_ready`
- `pilot_needs_remediation`
- `pilot_blocked`

## Next Phase After Step 12

If Step 12 is closed with `pilot_ready`, the next phase should be a tightly controlled human-reviewed activation procedure for real provider operations, still guarded by governance and explicit publish controls.
