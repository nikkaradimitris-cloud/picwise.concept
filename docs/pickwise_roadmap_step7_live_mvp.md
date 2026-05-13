# PickWise Roadmap Step 7 - Live MVP

## Purpose

Roadmap Step 7 introduces a controlled readiness and exposure layer for a small approved MVP batch.  
This step does not mass publish candidate pages, does not replace existing `/best` behavior, and does not broaden live sitemap inclusion.

Step 7 consumes Step 6 index-gate outcomes and determines which candidate pages are safe for:

- private preview readiness
- outbound click tracking contract readiness
- limited future public exposure eligibility (still controlled)

## Contract states and their meaning

- `candidate page`: a planned page record created in Step 5.
- `index_candidate`: a Step 6 status meaning the candidate satisfies index-quality gate criteria.
- `live_mvp_ready`: a Step 7 status meaning the candidate is approved for controlled MVP readiness.
- `public page`: a route that is actually exposed on public `/best/{slug}` and potentially included in a live sitemap.

A candidate can be `index_candidate` and still not become a public page in Step 7.  
Step 7 is readiness and control, not broad publication.

## Why Step 7 is controlled (not mass publish)

The Step 7 gate enforces:

- only Step 6 `index_candidate` records can become `live_mvp_ready`
- non-index Step 6 outcomes (`noindex_candidate`, `hold_manual_review`, `rejected`, `duplicate_canonical_required`) remain non-ready
- strict batch limits to keep MVP exposure intentionally small
- `is_mass_publish = false` for every record

This keeps rollout risk bounded while preserving existing closed gate guarantees.

## Preview and readiness behavior

Step 7 creates deterministic readiness fields per candidate:

- `can_render_preview`
- `can_collect_outbound_click`
- `can_be_publicly_exposed`
- `can_be_sitemap_candidate`

A page can be preview-ready without being publicly exposed.  
`can_be_publicly_exposed` remains policy-controlled and false by default.

## Outbound click tracking contract

Step 7 defines event-name contracts only, without adding live analytics integration:

- `live_mvp_preview_rendered`
- `live_mvp_outbound_click`

These are contractual event names attached to readiness records and can be wired to analytics later in a controlled way.

## Sitemap candidate vs live sitemap inclusion

`can_be_sitemap_candidate` in Step 7 is candidate-level metadata only.  
Step 7 does not write, mutate, or expand the live sitemap output route.

This preserves the existing sitemap behavior while preparing candidate-level inclusion signals for later steps.

## Evidence required to close Step 7

Step 7 closure evidence requires:

- deterministic Live MVP gate contracts and batch outputs
- tests proving non-index Step 6 outcomes cannot become `live_mvp_ready`
- tests proving selected clean MVP batch becomes `live_mvp_ready` with no blocks/holds
- tests proving no `/best` route replacement and no live sitemap expansion
- tests proving no new scraping/live provider calls/live Google API calls/credentials

## What Step 8 should measure next

Step 8 should measure controlled MVP performance and safety signals, such as:

- preview-to-approved-public conversion quality
- outbound click contract event coverage and integrity
- manual-review throughput and blocker reason trends
- limited sitemap-candidate activation outcomes under strict release controls
