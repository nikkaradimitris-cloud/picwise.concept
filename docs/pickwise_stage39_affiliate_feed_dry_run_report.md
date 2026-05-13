# PickWise Stage 39 - Affiliate Feed Dry-Run Import + Gate Pass Report

## What Stage 39 adds

Stage 39 adds a dry-run reporting layer at `src/picwise_offers/feed_dry_run.py` for local affiliate feed rows.

- Accepts local `list[dict]` rows only.
- Uses Stage 38 `adapt_affiliate_feed_rows()` to produce deterministic mapped/review/rejected outcomes.
- Runs mapped candidates through existing `run_product_eligibility_gate()` without changing gate rules.
- Attempts recommendation compatibility only for safe eligible candidates.
- Produces a deterministic readiness report for pre-publication assessment.

## What Stage 39 does not add

This stage is additive and non-breaking.

- No page publishing.
- No public route wiring.
- No sitemap writes or sitemap expansion.
- No live API calls.
- No scraping.
- No credentials.
- No fabrication of seller trust, shipping/returns, specs, taxonomy, descriptions, prices, or affiliate links.

## How dry-run reports help before 3,000 candidate pages

Raw feed quality is uneven at scale. The dry-run report surfaces deterministic blockers early:

- how many rows are mapped versus review-required/rejected,
- how many candidates pass eligibility as-is,
- how many are recommendation-ready under safe constraints,
- which missing fields and reason codes are most common.

This allows controlled remediation before any large candidate-to-page generation step.

## Why raw affiliate feeds may fail quality gates

Affiliate feeds often omit data required by strict page/index quality controls:

- missing image or price,
- unknown seller reliability,
- absent shipping/return policy signals,
- incomplete taxonomy linkage,
- invalid or missing URLs,
- thin metadata and comparison context.

Stage 39 does not bypass these requirements; it reports them.

## Data that must be enriched before page generation

Before moving to high-volume page candidates, data should be enriched from trusted upstream sources:

- seller reliability status (trusted/acceptable, not unknown),
- shipping and return policy availability,
- useful specifications and category/taxonomy linkage,
- complete, valid product media and pricing,
- stable outbound/affiliate link integrity.

## Why this stage does not publish or index anything

Stage 39 is a preflight quality-readiness step. It intentionally remains out of publish/index pipelines so existing public quality controls remain unchanged and no unqualified content reaches `/best` routes or sitemaps.

## Recommended next stage

Stage 40 should implement controlled enrichment input contracts and remediation workflows for high-frequency blocker categories, then rerun dry-run + gate reports on larger local batches before any tightly limited candidate-page pilot.
