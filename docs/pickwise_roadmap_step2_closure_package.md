# PickWise Roadmap Step 2 Closure Package

This document defines the **Roadmap Step 2 closure package** for real product and affiliate source intake.  
It is a closure decision layer, not a new publishing stage.

## Why this package exists

Stage 38 adapter, Stage 39 dry-run, and Stage 40 enrichment/remediation were necessary building blocks, but they were not sufficient to close Step 2 on their own:

- Stage 38 proves row mapping and rejection/review behavior.
- Stage 39 proves deterministic intake diagnostics and readiness blockers.
- Stage 40 proves controlled remediation without fabricated enrichment.
- Provider readiness evaluation proves threshold compliance.

Step 2 closes only when all of those outputs are evaluated together against the required product/feed field proof.

## Required Step 2 field proof (1-9 together)

Step 2 closure proof requires strict coverage evidence for all selected usable rows across the nine mandatory fields:

1. `title`
2. `image`
3. `price`
4. `description`
5. `specs`
6. `availability`
7. `merchant/seller`
8. `affiliate link`
9. `category data`

The closure contract reports:

- `total_rows`
- `field_coverage` for each field above
- `rows_missing_each_field`
- `adapter_summary`
- `dry_run_summary`
- `remediation_summary`
- `provider_readiness_summary`
- `step2_closure_status` (`step2_closed` / `step2_not_ready`)
- `can_move_to_step3`
- `blockers`
- `required_provider_fixes`
- `evidence_summary`

## What is required for `step2_closed`

`step2_closed` is only possible when all strict controls pass:

- All required fields 1-9 meet strict coverage threshold for usable rows.
- Rejected selected rows are zero.
- Review-required selected rows are at or below strict threshold.
- Provider readiness evaluator status is `step2_ready`.
- `can_move_to_step3` is true.
- No fabricated enrichment is detected.
- No public routes/sitemap/naming changes are involved.
- No live API calls, scraping, or credentials are used.

If any condition fails, closure is `step2_not_ready` and explicit blockers are returned.

## What blocks moving to Step 3

Examples of closure blockers:

- Any gap in required fields 1-9 (for selected usable rows).
- Missing monetization linkage (`affiliate link`) where monetization is expected.
- Missing category/taxonomy evidence.
- Missing merchant/seller identity or unresolved trust signals.
- Locale/market/currency mismatch findings.
- Any rejected selected rows.
- Provider evaluator threshold failures.

## Scope and non-goals

This package is additive and non-breaking. It does not:

- publish pages,
- wire content into public `/best` routes,
- expand sitemap URLs,
- generate 3,000 candidate pages,
- add scraping,
- add live API calls,
- add credentials,
- fabricate product/feed fields.

The package is a deterministic closure proof for Step 2 readiness only.
