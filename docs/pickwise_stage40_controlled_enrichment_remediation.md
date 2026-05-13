# PickWise Stage 40: Controlled Enrichment Contracts + Remediation Workflow

## What Stage 40 adds

Stage 40 adds a new local-only enrichment and remediation workflow for affiliate feed dry-run candidates:

- `src/picwise_offers/feed_enrichment.py` introduces controlled enrichment contracts.
- The contracts allow trusted explicit input maps for:
  - seller reliability mapping
  - shipping information coverage
  - return policy coverage
  - taxonomy/category linkage coverage
  - specification/description completeness
  - affiliate URL availability
  - locale/market/currency consistency review expectations
- The workflow emits deterministic remediation actions and deterministic per-candidate remediation results.
- Stage 39 dry-run is extended with an optional additive enrichment/remediation summary field.

## What Stage 40 does not add

Stage 40 does not:

- publish candidate pages
- index candidate pages
- modify public `/best` routes
- expand sitemap limits
- call live APIs
- scrape websites
- add affiliate credentials
- fabricate missing production fields

This stage remains non-breaking and additive.

## Why enrichment must be controlled

Missing seller trust, shipping, returns, taxonomy, specs, and affiliate link details are high-risk quality fields. Auto-filling these without explicit trusted input would weaken quality gates and create unsafe recommendations.

Controlled enrichment means:

- only local rows/candidates are accepted
- only explicit trusted enrichment maps are accepted
- no invented values are generated
- unresolved gaps are surfaced as deterministic remediation actions

## Fields that require trusted explicit input

The following fields can only be enriched from explicit trusted maps and are never fabricated:

- seller reliability status
- shipping info availability
- return policy availability
- taxonomy/category linkage
- specifications or short description completeness
- affiliate URL
- expected locale/market/currency mappings for review checks

## How this helps prepare 3,000 candidate pages

Stage 40 provides a deterministic remediation contract that can be used by internal operations and data pipelines to:

- classify every candidate as ready, needs remediation, or blocked
- identify exactly which fields are missing
- track what enrichment was explicitly applied
- separate auto-safe continuation from manual review requirements

This reduces ambiguity before scaling to a 3,000 candidate-page dry-run target while preserving strict gates.

## Why this still does not publish or index anything

The Stage 40 workflow only evaluates and summarizes candidate readiness in dry-run mode. It does not alter public route registration, does not modify sitemap publication behavior, and does not change search/index quality gates.

## Recommended next stage

Recommended Stage 41 focus:

- Build a local remediation queue/reporting layer that groups Stage 40 actions by owner (feed ops, taxonomy, compliance, affiliate links).
- Add deterministic SLA-style metrics for remediation closure rates.
- Keep publication/indexing disabled until remediation coverage reaches strict quality thresholds.
