# PickWise Roadmap Step 2: Provider Contract Hardening + Readiness Thresholds

## Scope and stage boundary

This document covers Roadmap Step 2 only.

It hardens the provider/feed contract for real product and affiliate source intake and defines deterministic readiness thresholds required before Step 2 can be considered closed.

This is additive and non-breaking. It does not move to Step 3, does not start 3,000 candidate pages, and does not change closed systems.

## Provider/feed contract requirements

Provider rows must satisfy explicit contract classes:

- `required_core`
- `required_for_public_candidate`
- `enrichment_allowed_from_trusted_map`
- `optional`
- `forbidden_to_fabricate`

### Required core fields

- product id or deterministic external id
- title
- product URL or outbound URL
- image URL
- price
- currency
- availability
- merchant or seller
- category or taxonomy signal
- locale or market signal where available

### Strongly required for public candidate readiness

- affiliate URL when monetization is expected
- seller reliability status from trusted mapping
- shipping information
- return policy information
- useful specifications or description
- category or taxonomy linkage
- locale, market, and currency consistency

### Optional but useful

- brand
- model
- GTIN/EAN/MPN where available
- rating/reviews only if provider supplies real values
- sale price only if provider supplies real values

## Fields that must never be fabricated

The hardened contract explicitly forbids fabrication of:

- seller trust/reliability
- shipping and return policy information
- taxonomy linkage
- specs/description completeness
- affiliate URL
- title, price, currency, availability, merchant/seller
- ratings/reviews and sale pricing
- locale/market/currency consistency signals

If these are missing, they remain missing and block readiness or require remediation.

## Allowed trusted remediation maps

Controlled enrichment is permitted only from explicit trusted maps:

- `trusted_seller_reliability_by_name`
- `shipping_info_available_by_candidate_id`
- `return_policy_available_by_candidate_id`
- `taxonomy_linkage_by_candidate_id`
- `specs_or_description_by_candidate_id`
- `affiliate_url_by_candidate_id`
- `locale_market_currency_by_candidate_id`
- `expected_currency_by_market`

No implicit enrichment or synthetic generation is allowed.

## Step 2 readiness thresholds

`evaluate_provider_batch_readiness(...)` enforces deterministic thresholds:

- rejected rate must be 0 for selected provider batch
- review-required rate must stay below strict threshold
- seller trust coverage must meet threshold
- image coverage must meet threshold
- price/currency coverage must meet threshold
- affiliate URL coverage must meet threshold when monetized
- shipping coverage must meet threshold
- return policy coverage must meet threshold
- specs/description coverage must meet threshold
- locale/currency mismatch rate must be 0 or blocked
- no fabricated enrichment
- no public route/sitemap changes
- no live API/scraping/credentials

## Readiness statuses

The evaluator returns one of:

- `step2_not_ready`
- `step2_conditionally_ready`
- `step2_ready`

And always returns:

- passed thresholds
- failed thresholds
- blockers
- required provider improvements
- allowed remediation inputs
- `can_move_to_step3`

## Why Step 2 is not closed yet by default

Step 2 is not closed until a real provider batch passes the hardened contract with zero hard blockers and full threshold compliance under deterministic evaluation.

Any rejected rows, locale/currency mismatches, missing monetization links (when expected), or unresolved trust/shipping/returns/specs gaps keeps Step 2 open.

## Evidence required before moving to Step 3

Before Step 3 can start, evidence must exist for a selected provider batch:

- deterministic dry-run report (Stage 39)
- deterministic remediation summary where needed (Stage 40)
- evaluator output with `status=step2_ready`
- no rejected rows and no unresolved locale/currency mismatches
- threshold pass list showing complete required coverage
- confirmation that no routes/sitemap/public labels changed
- confirmation that no product/SEO/index gates were relaxed

## Why this does not publish or index anything

This work validates readiness only. It does not create public candidate pages, does not wire anything into public `/best` routes, and does not expand sitemap publication scope.
