# PickWise Roadmap Step 5 - 3,000 Candidate Pages

## Step 5 purpose

Step 5 defines and validates a deterministic contract for building candidate buying page records from local, closed inputs:

- Step 2 provider-ready product evidence
- Step 3 locale-ready product eligibility evidence
- Step 4 page-ready keyword clusters

This step proves planning and batch-building capability for a 3,000 candidate-page target without publishing any page.

## Candidate pages are not public pages

Candidate pages in Step 5 are internal planning records only:

- not public routes
- not indexable
- not sitemap entries
- not routed under live `/best` endpoints

Every Step 5 candidate record is hard-set to:

- `is_public = false`
- `is_indexable = false`
- `sitemap_included = false`

## Step 5 inputs

`build_candidate_page_batch(...)` accepts explicit local inputs only:

- `keyword_clusters`
- `products`
- `locale_decisions`
- optional `recommendation_mapping`
- `max_candidate_pages` (default `3000`)

No scraping, live APIs, credentials, or provider calls are introduced in this stage.

## Core candidate-page rules

Step 5 enforces the following deterministic rules:

1. Use only Step 4 page-ready clusters.
2. Use only Step 2 provider-ready products.
3. Use only Step 3 locale-ready products for the target market.
4. Build one candidate page record per keyword cluster intent target.
5. Select 4 products where evidence allows.
6. If fewer than 4 products are available, keep candidate blocked with `needs_four_products`.
7. Keep recommendation deterministic:
   - use explicit recommendation map when valid
   - fallback to deterministic score evidence when unique
8. Detect duplicate slugs and block duplicate records.

## Candidate status and blocked/needs states

Candidate records can resolve to:

- `candidate_ready`
- `needs_products`
- `needs_locale`
- `needs_keywords`
- `needs_four_products`
- `duplicate_slug_blocked`
- `blocked`

Batch summary returns status and blocker counts for closure evidence.

## What closes Step 5

Step 5 closure evidence requires:

- deterministic batch outputs for identical inputs
- strict non-public/non-indexable/non-sitemap flags on all candidate records
- 4-product candidate readiness evidence for ready records
- deterministic duplicate-slug blocking
- deterministic local-input planning summary proving 3,000 target slot feasibility
- `can_move_to_step6 = true` only when strict blocker states are zero and planning capacity satisfies requested count

## What Step 6 decides next

Step 6 is responsible for quality and publication decisions, including:

- quality gates for index eligibility
- public route eligibility
- sitemap inclusion eligibility
- publish/no-publish decisions

Step 5 does not make or relax Step 6 decisions.
