# PickWise Roadmap Step 2 - Real Feed Sample Validation

## Scope and roadmap position

This document covers additive validation work for **Roadmap Step 2: Real product / affiliate source**.

The goal is to validate local feed quality using a realistic affiliate-provider-like sample, without changing public behavior and without progressing to large-scale page generation.

## What this sample feed represents

`tests/fixtures/roadmap_step2_real_feed_sample.json` is a local fixture shaped like exports from affiliate or merchant providers (for example, Linkwise-style product feeds).

It includes realistic row-level fields commonly present in provider exports:

- product identity (`product_id`, `title`, `brand`, `model`)
- seller identity (`merchant`/`seller`)
- commerce links (`product_url`, optional `affiliate_url`)
- media (`image_url`)
- pricing and stock (`price`, `currency`, `availability`)
- category/taxonomy context (`category`, `category_bucket`, `google_taxonomy_path`)
- content coverage (`description`, `specifications`)
- policy coverage (`shipping_info_available`, `return_policy_available`)
- market context (`locale`, `market`)

The fixture intentionally mixes quality states:

- rows that are ready or near-ready
- rows with missing seller trust mapping
- rows with missing shipping/returns
- rows with missing image
- rows with missing description/specifications
- rows with missing `affiliate_url` but valid `product_url`
- rows with locale/market/currency mismatch
- rows that must be rejected (invalid core URL contract)

## Required fields from a real affiliate/product provider

To move from intake to candidate-page-safe readiness under current gates, provider coverage generally must include:

- stable product ID and title
- seller/merchant identity
- valid outbound product URL
- valid image URL for retail products
- price and currency with market consistency
- taxonomy linkage (`category_bucket` or `google_taxonomy_path`)
- trusted seller reliability mapping (from explicit trusted source)
- shipping and return policy coverage (explicitly provided)
- non-fabricated product detail coverage (description/specifications)
- optional but expected affiliate deep-link coverage for production monetization flows

## Common blockers for public/index readiness

Rows commonly fail readiness when one or more of the following are missing or invalid:

- unknown seller trust
- missing shipping policy or return policy signals
- missing image, missing price, or invalid URL
- missing taxonomy linkage
- missing product detail depth (specs/description)
- locale/market/currency mismatch that requires manual review
- rejected core row contracts from source adapter checks

These blockers are intentionally surfaced and not auto-fixed with fake values.

## What must be solved before Step 2 can be closed

Step 2 can be considered closed only when validation consistently demonstrates:

- deterministic Stage 38 adaptation outcomes with low reject/review rates
- deterministic Stage 39 dry-run readiness with no unresolved publish-risk blockers
- deterministic Stage 40 remediation outputs with explicit trusted enrichment inputs
- no fake enrichment behavior and no relaxed eligibility/index gates
- stable seller trust, shipping/returns, taxonomy, and description/spec coverage from real provider data contracts

## Why this does not create 3,000 pages yet

This validation remains local and pre-publication by design:

- it does not wire rows into public `/best` routes
- it does not expand sitemap outputs
- it does not publish/index pages
- it does not add scraping, live APIs, or credentials

Step 2 validation proves data-contract and remediation readiness first. High-volume candidate-page generation remains blocked until quality blockers are resolved under existing strict gates.
