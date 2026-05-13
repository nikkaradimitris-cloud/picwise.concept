# PickWise Roadmap Step 4 - Selected Clean Keyword Batch Closure Proof

## What this package is

This package is the Step 4 closure proof for keyword source and keyword cluster contracts.
It is intentionally scoped to validation evidence only, using a selected clean batch that is page-ready by contract rules.

It does not move implementation into Step 5 and does not generate or publish any pages.

## Why the previous full fixture did not close Step 4

The full mixed fixture includes intentional negative cases for deterministic guardrail coverage:

- missing or invalid main keyword shapes
- insufficient or excessive long-tail patterns
- informational-only intent for buying-page scope
- ambiguous intent requiring review
- duplicate-heavy/stuffing patterns
- locale/market mismatches

Those records are expected to keep `can_move_to_step5=false` for the mixed batch because the batch contains blocked clusters by design.

## What makes the selected batch clean

The selected clean fixture contains only page-ready clusters:

- US English buyer-intent cluster
- UK English buyer/comparison cluster
- DE German buyer-intent cluster
- GR Greek/Greeklish buyer-intent cluster
- product-specific brand/model/spec cluster

Each cluster keeps contract-safe structure:

- exactly 1 main keyword
- 3-5 support keywords
- 10-30 long-tail keywords
- clear buyer/comparison/product-specific intent
- valid locale-market combinations for US/UK/DE/GR
- product/category linkage via category text and/or spec/brand-model signals
- no duplicate-heavy output and no keyword stuffing
- explicit volume buckets only (`low`, `medium`, `high`, `unknown`)
- no fabricated numeric volume claims

## Evidence that `can_move_to_step5=true`

The closure-proof tests for the selected clean batch assert:

- fixture loads and contains expected coverage clusters
- every cluster validates as `page_ready`
- batch validator returns `blocked_count=0`
- `review_required_count` stays within strict threshold (0 in this package)
- batch gate returns `can_move_to_step5=true`
- language variants are preserved (English spelling variants, German, Greek + Greeklish)
- unknown volume bucket is preserved where explicit real volume is not provided
- no naming/routes/sitemap/public label behavior changes
- no gate relaxation and no scraping/live Google API/credentials usage

## Why this still does not create pages

Step 4 closure here validates keyword contract readiness only.
It does not create candidate pages, does not publish routes, and does not expand sitemap output.
Public `/best` behavior remains unchanged.

## What Step 5 should do next

Step 5 should consume only validated Step 4-ready clusters and then:

1. run controlled candidate-page generation in bounded batches,
2. apply existing publication/SEO/index quality gates unchanged,
3. keep routing and sitemap expansion gated behind explicit approval and tests,
4. preserve source provenance and volume-bucket honesty in downstream artifacts.
